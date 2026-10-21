"""Busca de projetos e votações (GET /projetos).

Une quatro origens numa lista só:
- proposições federais (tabela `proposicao`, inclusive as de origem "votada");
- proposições votadas que só existem em `votacao` (rótulo e ementa gravados na votação);
- projetos locais (`projeto_local`: câmaras municipais e assembleias);
- votações locais (`votacao_local`) que não estão ligadas a um projeto local.

Ordem (`ordem`):
- "informacao" (padrão): primeiro os itens com mais informação publicada (`nivel`, uma contagem
  de itens que existem ou não; ver NIVEL), depois a data da última votação nominal e a da última
  movimentação, da mais recente para a mais antiga.
- "recentes": o que está na pauta primeiro (a data mais próxima), depois a data da última
  votação ou movimentação, da mais recente para a mais antiga.
Nunca relevância editorial: assunto, partido, autor, resultado e placar não entram na ordem.

`q` reconhece número ("PL 2338/2023", "pl 2338", "PL nº 2.338, de 2023", "2338/2023"); fora
disso são palavras na ementa, todas exigidas, sem acento (app/services/texto_busca.py).
`uf` e `municipio` valem para o que é local; `tema` vale só para o federal (a classificação
oficial por tema existe só no Congresso). Decisões em docs/DECISOES.md, 2026-10-21."""

import re
from collections import defaultdict
from datetime import date

import sqlalchemy as sa
from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.models import (
    CanalOficial,
    Discurso,
    MandatoLocal,
    Municipio,
    PautaItem,
    ProjetoLocal,
    Proposicao,
    ProposicaoTema,
    Tramitacao,
    Votacao,
    VotacaoLocal,
)
from app.services import discursos_projeto, projeto_fontes, texto_busca
from app.services.projeto_detalhe import _contagens, escolher_principal
from ingestion.proposicoes_comum import SEM_CLASSIFICACAO

POR_PAGINA = 20
SIGLAS = {
    "PL", "PLP", "PLC", "PLS", "PLV", "PLN", "PEC", "PDL", "PDC", "PDS", "MPV", "MP", "PRC",
    "PRS", "PR", "PRE", "REQ", "RIC", "INC", "VET",
}  # fmt: skip
# Rótulo de projeto local começa pelo nome do tipo ("Projeto de Lei Ordinária"): sigla -> (ilike,
# ilike a excluir).
TIPO_LOCAL = {
    "PL": ("Projeto de Lei%", "%complementar%"),
    "PLC": ("Projeto de Lei Complementar%", None),
    "PLP": ("Projeto de Lei Complementar%", None),
    "PEC": ("Proposta de Emenda%", None),
    "PDL": ("Projeto de Decreto%", None),
    "PR": ("Projeto de Resolu%", None),
    "PRE": ("Projeto de Resolu%", None),
    "REQ": ("Requerimento%", None),
    "VET": ("Veto%", None),
}
ORDENS = ("informacao", "recentes")
# Nível de informação publicada: quantos destes itens o projeto tem (cada um vale 1). Só a presença
# do dado conta, nunca o conteúdo. Decisão em docs/DECISOES.md, 2026-10-21 ("Ordem por informação").
NIVEL = {
    "proposicao": [
        "votação nominal (ao menos uma)",
        "discursos ligados ao projeto",
        "caminho (passos da tramitação)",
        "situação publicada",
        "tema oficial",
    ],
    "projeto_local": ["votação nominal ligada", "ementa", "situação (em tramitação ou não)"],
    "votacao_local": ["votação nominal (sempre)", "ementa da matéria", "resultado"],
}
LOCAL_POR_CASA = {"assembleia": "assembleia", "camara_municipal": "camara"}
CASA_DO_LOCAL = {"assembleia": "assembleia", "camara": "camara_municipal"}

_NUMERO = re.compile(
    r"""^\s*(?:(?P<sigla>[A-Za-z]{2,4})\s*\.?\s*)?
        (?:n[º°o]?\.?\s*)?
        (?P<numero>\d{1,3}(?:\.\d{3})+|\d{1,6})
        \s*(?:(?:/|,?\s*de\s+)\s*(?P<ano>\d{4}))?\s*$""",
    re.IGNORECASE | re.VERBOSE,
)


def reconhecer_numero(q: str) -> dict | None:
    """{"sigla", "numero", "ano"} quando `q` é um número de projeto; senão None."""
    achou = _NUMERO.match(q)
    if not achou:
        return None
    sigla = achou["sigla"].upper() if achou["sigla"] else None
    if sigla and sigla not in SIGLAS:
        return None
    if sigla == "MP":  # medida provisória: a sigla oficial nas bases é MPV
        sigla = "MPV"
    return {
        "sigla": sigla,
        "numero": int(achou["numero"].replace(".", "")),
        "ano": int(achou["ano"]) if achou["ano"] else None,
    }


def _combina(coluna: str, termo: str):
    """Todas as palavras do termo na coluna de texto (mesma expressão do índice)."""
    return literal_column(texto_busca.sql_tsvector(coluna)).op("@@")(
        func.plainto_tsquery(literal_column("'portuguese'"), texto_busca.palavras(termo))
    )


_nulo_texto = sa.cast(sa.null(), sa.String)
_nulo_data = sa.cast(sa.null(), sa.Date)


def _ultima_votacao_por_projeto():
    return (
        select(
            Votacao.casa.label("casa"),
            Votacao.proposicao_id_externo.label("pid"),
            func.max(Votacao.data).label("data_ult"),
        )
        .where(Votacao.proposicao_id_externo.is_not(None))
        .group_by(Votacao.casa, Votacao.proposicao_id_externo)
        .subquery("vot")
    )


def _ultima_tramitacao():
    return (
        select(
            Tramitacao.casa.label("casa"),
            Tramitacao.proposicao_id_externo.label("pid"),
            sa.cast(func.max(Tramitacao.data), sa.Date).label("data_ult"),
        )
        .group_by(Tramitacao.casa, Tramitacao.proposicao_id_externo)
        .subquery("tram")
    )


def _discursos_por_projeto():
    return (
        select(
            Discurso.casa.label("casa"),
            Discurso.proposicao_id_externo.label("pid"),
            func.count().label("n"),
        )
        .where(Discurso.proposicao_id_externo.is_not(None))
        .group_by(Discurso.casa, Discurso.proposicao_id_externo)
        .subquery("disc")
    )


def _tem_tema(casa, pid):
    """Tem tema oficial (sem contar "Sem classificação"). Subconsulta sem correlação: o Postgres
    monta uma tabela de hash uma vez e só consulta por linha (correlacionada, sondava o índice a
    cada linha e custava 4 vezes mais)."""
    com_tema = select(ProposicaoTema.casa, ProposicaoTema.proposicao_id_externo).where(
        ProposicaoTema.tema != SEM_CLASSIFICACAO
    )
    return sa.tuple_(casa, pid).in_(com_tema)


def _tem(condicao):
    """1 quando a condição vale, 0 senão (para somar o nível de informação)."""
    return sa.case((condicao, 1), else_=0)


def _texto_ok(coluna):
    return coluna.is_not(None) & (func.length(func.trim(coluna)) > 0)


def _proxima_pauta(hoje: date):
    return (
        select(
            PautaItem.casa.label("casa"),
            PautaItem.proposicao_id_externo.label("pid"),
            func.min(PautaItem.data).label("data"),
        )
        .where(PautaItem.data >= hoje, PautaItem.proposicao_id_externo.is_not(None))
        .group_by(PautaItem.casa, PautaItem.proposicao_id_externo)
        .subquery("pauta")
    )


def _federais(f: dict, hoje: date) -> list:
    """Consultas A (proposicao) e B (só em votacao), no formato comum da união."""
    vot, tram, pauta = _ultima_votacao_por_projeto(), _ultima_tramitacao(), _proxima_pauta(hoje)
    disc = _discursos_por_projeto()
    numero = f["numero"]
    rotulo_a = func.concat(Proposicao.sigla_tipo, " ", Proposicao.numero, "/", Proposicao.ano)
    a = (
        select(
            sa.literal_column("'proposicao'").label("tipo"),
            Proposicao.casa.label("casa"),
            _nulo_texto.label("uf"),
            _nulo_texto.label("municipio_ibge"),
            _nulo_texto.label("municipio"),
            Proposicao.id_externo.label("ref"),
            rotulo_a.label("rotulo"),
            Proposicao.ementa.label("ementa"),
            Proposicao.situacao.label("situacao"),
            Proposicao.virou_lei.label("virou_lei"),
            func.greatest(vot.c.data_ult, tram.c.data_ult, Proposicao.data_apresentacao).label(
                "data_ord"
            ),
            pauta.c.data.label("na_pauta"),
            (
                _tem(vot.c.data_ult.is_not(None))
                + _tem(disc.c.pid.is_not(None))
                + _tem(tram.c.pid.is_not(None))
                + _tem(_texto_ok(Proposicao.situacao))
                + _tem(_tem_tema(Proposicao.casa, Proposicao.id_externo))
            ).label("nivel"),
            vot.c.data_ult.label("data_vot"),
        )
        .select_from(Proposicao)
        .outerjoin(vot, (vot.c.casa == Proposicao.casa) & (vot.c.pid == Proposicao.id_externo))
        .outerjoin(tram, (tram.c.casa == Proposicao.casa) & (tram.c.pid == Proposicao.id_externo))
        .outerjoin(
            pauta, (pauta.c.casa == Proposicao.casa) & (pauta.c.pid == Proposicao.id_externo)
        )
        .outerjoin(disc, (disc.c.casa == Proposicao.casa) & (disc.c.pid == Proposicao.id_externo))
    )
    if f["casa_federal"]:
        a = a.where(Proposicao.casa == f["casa_federal"])
    if numero:
        a = a.where(Proposicao.numero == numero["numero"])
        if numero["sigla"]:
            a = a.where(Proposicao.sigla_tipo == numero["sigla"])
        if numero["ano"]:
            a = a.where(Proposicao.ano == numero["ano"])
    elif f["palavras"]:
        a = a.where(_combina("proposicao.ementa", f["palavras"]))
    if f["ano"]:
        a = a.where(Proposicao.ano == f["ano"])
    if f["tema"]:
        a = a.where(
            select(ProposicaoTema.tema)
            .where(
                ProposicaoTema.casa == Proposicao.casa,
                ProposicaoTema.proposicao_id_externo == Proposicao.id_externo,
                ProposicaoTema.tema == f["tema"],
            )
            .exists()
        )
    if f["votacao"] == "com":
        a = a.where(vot.c.data_ult.is_not(None))
    elif f["votacao"] == "sem":
        a = a.where(vot.c.data_ult.is_(None))

    # B: votadas que só existem na tabela de votações.
    tram_b, pauta_b = _ultima_tramitacao(), _proxima_pauta(hoje)
    disc_b = _discursos_por_projeto()
    g = (
        select(
            Votacao.casa.label("casa"),
            Votacao.proposicao_id_externo.label("pid"),
            func.max(Votacao.proposicao).label("rotulo"),
            func.max(Votacao.proposicao_ementa).label("ementa"),
            func.max(Votacao.data).label("data_ult"),
        )
        .where(Votacao.proposicao_id_externo.is_not(None))
        .group_by(Votacao.casa, Votacao.proposicao_id_externo)
        .subquery("g")
    )
    b = (
        select(
            sa.literal_column("'proposicao'").label("tipo"),
            g.c.casa.label("casa"),
            _nulo_texto.label("uf"),
            _nulo_texto.label("municipio_ibge"),
            _nulo_texto.label("municipio"),
            g.c.pid.label("ref"),
            func.coalesce(g.c.rotulo, func.concat("Proposição ", g.c.pid)).label("rotulo"),
            g.c.ementa.label("ementa"),
            _nulo_texto.label("situacao"),
            sa.cast(sa.null(), sa.Boolean).label("virou_lei"),
            func.greatest(g.c.data_ult, tram_b.c.data_ult).label("data_ord"),
            pauta_b.c.data.label("na_pauta"),
            (
                1  # votação nominal: sempre (só existe na tabela de votações)
                + _tem(disc_b.c.pid.is_not(None))
                + _tem(tram_b.c.pid.is_not(None))
                + _tem(_tem_tema(g.c.casa, g.c.pid))
            ).label("nivel"),
            g.c.data_ult.label("data_vot"),
        )
        .select_from(g)
        .outerjoin(tram_b, (tram_b.c.casa == g.c.casa) & (tram_b.c.pid == g.c.pid))
        .outerjoin(pauta_b, (pauta_b.c.casa == g.c.casa) & (pauta_b.c.pid == g.c.pid))
        .outerjoin(disc_b, (disc_b.c.casa == g.c.casa) & (disc_b.c.pid == g.c.pid))
        .where(
            ~select(Proposicao.id)
            .where(Proposicao.casa == g.c.casa, Proposicao.id_externo == g.c.pid)
            .exists()
        )
    )
    if f["casa_federal"]:
        b = b.where(g.c.casa == f["casa_federal"])
    if f["votacao"] == "sem":
        b = b.where(sa.false())
    if numero:
        sigla = numero["sigla"] or "[A-Za-z]+"
        ano = f"/{numero['ano']}" if numero["ano"] else "/"
        b = b.where(g.c.rotulo.op("~*")(f"^{sigla} +0*{numero['numero']}{ano}"))
    elif f["palavras"]:
        b = b.where(_combina("g.ementa", f["palavras"]))
    if f["ano"]:
        b = b.where(func.substring(g.c.rotulo, "/([0-9]{4})") == str(f["ano"]))
    if f["tema"]:
        b = b.where(
            select(ProposicaoTema.tema)
            .where(
                ProposicaoTema.casa == g.c.casa,
                ProposicaoTema.proposicao_id_externo == g.c.pid,
                ProposicaoTema.tema == f["tema"],
            )
            .exists()
        )
    return [a, b]


def _filtro_local(f: dict, coluna_casa, coluna_uf, coluna_ibge):
    condicoes = [coluna_casa.in_(f["casas_locais"])]
    if f["uf"]:
        condicoes.append(coluna_uf == f["uf"])
    if f["municipio"]:
        condicoes.append(coluna_ibge == f["municipio"])
    return condicoes


def _locais(f: dict) -> list:
    numero = f["numero"]
    # Votações locais que não estão ligadas a um projeto local (as ligadas aparecem no projeto).
    c = (
        select(
            sa.literal_column("'votacao_local'").label("tipo"),
            VotacaoLocal.casa.label("casa"),
            VotacaoLocal.uf.label("uf"),
            VotacaoLocal.municipio_ibge.label("municipio_ibge"),
            _nulo_texto.label("municipio"),  # o nome vem depois, só para a página
            sa.cast(VotacaoLocal.id, sa.String).label("ref"),
            VotacaoLocal.materia.label("rotulo"),
            VotacaoLocal.materia_ementa.label("ementa"),
            VotacaoLocal.resultado.label("situacao"),
            sa.cast(sa.null(), sa.Boolean).label("virou_lei"),
            VotacaoLocal.data.label("data_ord"),
            _nulo_data.label("na_pauta"),
            (
                1  # votação nominal: sempre
                + _tem(_texto_ok(VotacaoLocal.materia_ementa))
                + _tem(_texto_ok(VotacaoLocal.resultado))
            ).label("nivel"),
            VotacaoLocal.data.label("data_vot"),
        )
        .select_from(VotacaoLocal)
        .where(
            VotacaoLocal.projeto_local_id.is_(None),
            *_filtro_local(f, VotacaoLocal.casa, VotacaoLocal.uf, VotacaoLocal.municipio_ibge),
        )
    )
    vl = (
        select(
            VotacaoLocal.projeto_local_id.label("pid"),
            func.max(VotacaoLocal.data).label("data_ult"),
        )
        .where(VotacaoLocal.projeto_local_id.is_not(None))
        .group_by(VotacaoLocal.projeto_local_id)
        .subquery("vl")
    )
    d = (
        select(
            sa.literal_column("'projeto_local'").label("tipo"),
            MandatoLocal.casa.label("casa"),
            MandatoLocal.uf.label("uf"),
            ProjetoLocal.municipio_ibge.label("municipio_ibge"),
            _nulo_texto.label("municipio"),  # o nome vem depois, só para a página
            sa.cast(ProjetoLocal.id, sa.String).label("ref"),
            func.concat(
                ProjetoLocal.tipo,
                func.coalesce(func.concat(" nº ", ProjetoLocal.numero), ""),
                "/",
                ProjetoLocal.ano,
            ).label("rotulo"),
            ProjetoLocal.ementa.label("ementa"),
            sa.case(
                (ProjetoLocal.em_tramitacao.is_(True), "Em tramitação"),
                (ProjetoLocal.em_tramitacao.is_(False), "Fora de tramitação"),
                else_=None,
            ).label("situacao"),
            sa.cast(sa.null(), sa.Boolean).label("virou_lei"),
            func.coalesce(vl.c.data_ult, ProjetoLocal.data_apresentacao).label("data_ord"),
            _nulo_data.label("na_pauta"),
            (
                _tem(vl.c.pid.is_not(None))
                + _tem(_texto_ok(ProjetoLocal.ementa))
                + _tem(ProjetoLocal.em_tramitacao.is_not(None))
            ).label("nivel"),
            vl.c.data_ult.label("data_vot"),
        )
        .select_from(ProjetoLocal)
        .join(MandatoLocal, MandatoLocal.id == ProjetoLocal.mandato_id)
        .outerjoin(vl, vl.c.pid == ProjetoLocal.id)
        .where(*_filtro_local(f, MandatoLocal.casa, MandatoLocal.uf, ProjetoLocal.municipio_ibge))
    )
    if f["votacao"] == "com":
        d = d.where(vl.c.pid.is_not(None))
    elif f["votacao"] == "sem":
        d = d.where(vl.c.pid.is_(None))
        c = c.where(sa.false())

    if numero:
        c = c.where(
            VotacaoLocal.materia.op("~")(f"(^|[^0-9]){numero['numero']}([^0-9]|$)"),
        )
        d = d.where(ProjetoLocal.numero == numero["numero"])
        if numero["ano"]:
            c = c.where(VotacaoLocal.materia.op("~")(f"(^|[^0-9]){numero['ano']}([^0-9]|$)"))
            d = d.where(ProjetoLocal.ano == numero["ano"])
        if numero["sigla"]:
            padrao = TIPO_LOCAL.get(numero["sigla"])
            if padrao is None:
                c, d = c.where(sa.false()), d.where(sa.false())
            else:
                c = c.where(VotacaoLocal.materia.ilike(padrao[0]))
                d = d.where(ProjetoLocal.tipo.ilike(padrao[0]))
                if padrao[1]:
                    c = c.where(~VotacaoLocal.materia.ilike(padrao[1]))
                    d = d.where(~ProjetoLocal.tipo.ilike(padrao[1]))
    elif f["palavras"]:
        c = c.where(_combina("votacao_local.materia_ementa", f["palavras"]))
        d = d.where(_combina("projeto_local.ementa", f["palavras"]))
    if f["ano"]:
        c = c.where(func.extract("year", VotacaoLocal.data) == f["ano"])
        d = d.where(ProjetoLocal.ano == f["ano"])
    if f["tema"]:
        c, d = c.where(sa.false()), d.where(sa.false())
    return [c, d]


def _filtros(q, esfera, casa, uf, municipio, tema, ano, votacao) -> dict:
    q = (q or "").strip()
    numero = reconhecer_numero(q) if q else None
    federal = esfera in (None, "federal") and casa in (None, "camara", "senado")
    # uf e município só existem no que é local.
    federal = federal and not uf and not municipio
    casas_locais = []
    if esfera in (None, "estadual") and casa in (None, "assembleia"):
        casas_locais.append("assembleia")
    if esfera in (None, "municipal") and casa in (None, "camara_municipal"):
        casas_locais.append("camara")
    return {
        "q": q or None,
        "numero": numero,
        "palavras": None if numero else (texto_busca.palavras(q) or None),
        "federal": federal,
        "casa_federal": casa if casa in ("camara", "senado") else None,
        "casas_locais": casas_locais,
        "uf": uf.upper() if uf else None,
        "municipio": municipio,
        "tema": tema,
        "ano": ano,
        "votacao": votacao,
    }


def _ultimas_votacoes(session: Session, linhas: list) -> dict[tuple, dict]:
    """Votação principal (mesma regra do detalhe) de cada item da página, por (tipo, casa, ref)."""
    resultado: dict[tuple, dict] = {}
    federais = [(r.casa, r.ref) for r in linhas if r.tipo == "proposicao"]
    if federais:
        votacoes = session.scalars(
            select(Votacao).where(
                sa.tuple_(Votacao.casa, Votacao.proposicao_id_externo).in_(federais)
            )
        ).all()
        por_projeto: dict[tuple, list[Votacao]] = defaultdict(list)
        for v in votacoes:
            por_projeto[(v.casa, v.proposicao_id_externo)].append(v)
        ultimas = {
            chave: escolher_principal(sorted(vs, key=discursos_projeto.ordem_da_votacao))
            for chave, vs in por_projeto.items()
        }
        sem_publicado = [v.id for v in ultimas.values() if v.placar_sim is None]
        contagens = _contagens(session, sem_publicado)
        for (casa, pid), v in ultimas.items():
            sim, nao = (
                (v.placar_sim, v.placar_nao)
                if v.placar_sim is not None or v.placar_nao is not None
                else (contagens[v.id]["Sim"], contagens[v.id]["Não"])
            )
            resultado[("proposicao", casa, pid)] = {
                "data": v.data,
                "resultado": v.resultado,
                "sim": sim,
                "nao": nao,
                "descricao": v.descricao,
                "link": f"/votacao/{casa}/{v.id_externo}",
            }
    ids_votacao = [int(r.ref) for r in linhas if r.tipo == "votacao_local"]
    ids_projeto = [int(r.ref) for r in linhas if r.tipo == "projeto_local"]
    if ids_votacao or ids_projeto:
        locais = session.scalars(
            select(VotacaoLocal).where(
                VotacaoLocal.id.in_(ids_votacao) | VotacaoLocal.projeto_local_id.in_(ids_projeto)
            )
        ).all()

        def registro(v: VotacaoLocal) -> dict:
            return {
                "data": v.data,
                "resultado": v.resultado,
                "sim": v.sim,
                "nao": v.nao,
                "descricao": v.materia,
                "link": f"/votacao/local/{v.id}",
            }

        for v in locais:
            if v.id in ids_votacao:
                resultado[("votacao_local", v.casa, str(v.id))] = registro(v)
        ordem = sorted(locais, key=lambda v: (v.data or date.min, v.id))
        for v in ordem:  # a mais recente por último sobrescreve
            if v.projeto_local_id in ids_projeto:
                resultado[("projeto_local_ligada", "", str(v.projeto_local_id))] = registro(v)
    return resultado


def buscar(
    session: Session,
    q: str | None = None,
    esfera: str | None = None,
    casa: str | None = None,
    uf: str | None = None,
    municipio: str | None = None,
    tema: str | None = None,
    ano: int | None = None,
    votacao: str | None = None,
    pagina: int = 1,
    hoje: date | None = None,
    ordem: str = "informacao",
) -> dict:
    hoje = hoje or date.today()
    f = _filtros(q, esfera, casa, uf, municipio, tema, ano, votacao)
    consultas = []
    if f["federal"]:
        consultas += _federais(f, hoje)
    if f["casas_locais"]:
        consultas += _locais(f)

    if consultas:
        u = sa.union_all(*consultas).subquery("u")
        total = session.scalar(select(func.count()).select_from(u)) or 0
        if ordem == "recentes":
            criterio = [
                u.c.na_pauta.is_not(None).desc(),
                u.c.na_pauta.asc().nullslast(),
                u.c.data_ord.desc().nullslast(),
            ]
        else:
            criterio = [
                u.c.nivel.desc(),
                u.c.data_vot.desc().nullslast(),
                u.c.data_ord.desc().nullslast(),
            ]
        linhas = session.execute(
            select(u)
            .order_by(*criterio, u.c.rotulo, u.c.ref)
            .limit(POR_PAGINA)
            .offset((max(pagina, 1) - 1) * POR_PAGINA)
        ).all()
    else:
        total, linhas = 0, []

    ultimas = _ultimas_votacoes(session, linhas)
    contagens = _contagens_federais(session, linhas)
    ibges = {r.municipio_ibge for r in linhas if r.municipio_ibge}
    consulta_nomes = select(Municipio.ibge, Municipio.nome).where(Municipio.ibge.in_(ibges))
    nomes = {ibge: nome for ibge, nome in session.execute(consulta_nomes)} if ibges else {}
    itens = []
    for r in linhas:
        if r.tipo == "proposicao":
            esfera_item, casa_item = "federal", r.casa
            link = f"/projeto/{r.casa}/{r.ref}"
            ultima = ultimas.get(("proposicao", r.casa, r.ref))
        elif r.tipo == "votacao_local":
            casa_item = CASA_DO_LOCAL[r.casa]
            esfera_item = "estadual" if r.casa == "assembleia" else "municipal"
            link = f"/votacao/local/{r.ref}"
            ultima = ultimas.get(("votacao_local", r.casa, r.ref))
        else:
            casa_item = CASA_DO_LOCAL[r.casa]
            esfera_item = "estadual" if r.casa == "assembleia" else "municipal"
            link = f"/projeto/local/{r.ref}"
            ultima = ultimas.get(("projeto_local_ligada", "", r.ref))
        itens.append(
            {
                "tipo": r.tipo,
                "rotulo": r.rotulo,
                "ementa": r.ementa,
                "esfera": esfera_item,
                "casa": casa_item,
                "uf": r.uf,
                "municipio_ibge": r.municipio_ibge,
                "municipio": nomes.get(r.municipio_ibge),
                "situacao": r.situacao,
                "virou_lei": r.virou_lei,
                "ultima_votacao": ultima,
                "na_pauta": r.na_pauta,
                "ultima_movimentacao": r.data_ord,
                "link": link,
                "nivel_informacao": r.nivel,
                "discursos": contagens["discursos"].get((r.casa, r.ref), 0)
                if r.tipo == "proposicao"
                else None,
                "passos_caminho": contagens["passos"].get((r.casa, r.ref), 0)
                if r.tipo == "proposicao"
                else None,
            }
        )
    return {
        "q": f["q"],
        "total": total,
        "pagina": max(pagina, 1),
        "por_pagina": POR_PAGINA,
        "itens": itens,
        "fontes": _fontes(session),
        "ordem": ordem,
        "cobertura": _cobertura(session, f) if f["uf"] or f["municipio"] else None,
    }


def _contagens_federais(session: Session, linhas: list) -> dict[str, dict[tuple, int]]:
    """Discursos ligados e passos do caminho de cada projeto federal da página."""
    chaves = [(r.casa, r.ref) for r in linhas if r.tipo == "proposicao"]
    saida: dict[str, dict[tuple, int]] = {"discursos": {}, "passos": {}}
    if not chaves:
        return saida
    for nome, modelo in (("discursos", Discurso), ("passos", Tramitacao)):
        consulta = (
            select(modelo.casa, modelo.proposicao_id_externo, func.count())
            .where(sa.tuple_(modelo.casa, modelo.proposicao_id_externo).in_(chaves))
            .group_by(modelo.casa, modelo.proposicao_id_externo)
        )
        saida[nome] = {(c, p): n for c, p, n in session.execute(consulta)}
    return saida


TIPOS_CANAL_CAMARA = ("sapl", "sistema_legislativo", "camara")


def _cobertura(session: Session, f: dict) -> dict:
    """O que a lista tem (ou não) da cidade e do estado filtrados: se há dado da câmara e da
    assembleia aqui, e o site oficial da câmara, para explicar uma lista vazia."""
    uf = f["uf"]
    camara = None
    if f["municipio"]:
        municipio = session.get(Municipio, f["municipio"])
        if municipio is not None:
            uf = uf or municipio.uf
            ibge = municipio.ibge
            tem = session.scalar(
                select(
                    select(MandatoLocal.id)
                    .where(MandatoLocal.casa == "camara", MandatoLocal.municipio_ibge == ibge)
                    .exists()
                    | select(VotacaoLocal.id)
                    .where(VotacaoLocal.casa == "camara", VotacaoLocal.municipio_ibge == ibge)
                    .exists()
                    | select(ProjetoLocal.id).where(ProjetoLocal.municipio_ibge == ibge).exists()
                )
            )
            canais = {
                c.tipo: c.url
                for c in session.scalars(
                    select(CanalOficial).where(
                        CanalOficial.municipio_ibge == ibge,
                        CanalOficial.tipo.in_(TIPOS_CANAL_CAMARA),
                    )
                )
            }
            canal = next((canais[t] for t in TIPOS_CANAL_CAMARA if t in canais), None)
            camara = {
                "municipio_ibge": ibge,
                "municipio": municipio.nome,
                "tem_dados": bool(tem),
                "canal_url": canal,
            }
    assembleia = None
    if uf:
        tem = session.scalar(
            select(
                select(MandatoLocal.id)
                .where(MandatoLocal.casa == "assembleia", MandatoLocal.uf == uf)
                .exists()
                | select(VotacaoLocal.id)
                .where(VotacaoLocal.casa == "assembleia", VotacaoLocal.uf == uf)
                .exists()
            )
        )
        assembleia = {"uf": uf, "tem_dados": bool(tem)}
    return {"uf": uf, "camara": camara, "assembleia": assembleia}


def _fontes(session: Session) -> list[dict]:
    return [
        {
            "fonte_nome": "Proposições e votações da Câmara dos Deputados (Dados Abertos)",
            "fonte_url": "https://dadosabertos.camara.leg.br/",
            "atualizado_em": projeto_fontes.atualizado_em(
                session, ["camara_proposicoes", "camara_votacoes"]
            ),
        },
        {
            "fonte_nome": "Processos e votações do Senado Federal (Dados Abertos)",
            "fonte_url": "https://legis.senado.leg.br/dadosabertos/docs/",
            "atualizado_em": projeto_fontes.atualizado_em(
                session, ["senado_proposicoes", "senado_votacoes"]
            ),
        },
        projeto_fontes.fonte_local(session, "https://www.interlegis.leg.br/"),
    ]

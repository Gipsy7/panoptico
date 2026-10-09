"""Pessoa pública e linha do tempo, juntando todas as fontes ligadas à mesma pessoa.

Regra de publicação num lugar só: um registro de outra fonte só aparece se o vínculo
dele com a pessoa for forte (CPF, título, ligação do TSE) ou revisado à mão. Vínculo por
nome (vereador da câmara ligado ao eleito do TSE) fica de fora até ser revisado.
"""

from datetime import date

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    Caso,
    CasoDocumento,
    Evento,
    MandatoLocal,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
    Processo,
)
from app.models.pessoa import REGRAS_FORTES
from app.services import tse

# Data do 1º turno, para os cargos de turno único enquanto a candidatura não tem a data
# do turno (candidatura.data_eleicao vem da carga do TSE). Nos cargos com 2º turno, sem
# essa data, o evento fica sem data em vez de arriscar a errada.
PRIMEIRO_TURNO = {
    2018: date(2018, 10, 7),
    2020: date(2020, 11, 15),
    2022: date(2022, 10, 2),
    2024: date(2024, 10, 6),
    2026: date(2026, 10, 4),
}
DOIS_TURNOS = {"PRESIDENTE", "VICE-PRESIDENTE", "GOVERNADOR", "VICE-GOVERNADOR", "PREFEITO",
               "VICE-PREFEITO"}  # fmt: skip
FEMININO = {"deputado": "deputada", "vereador": "vereadora", "senador": "senadora",
            "governador": "governadora", "prefeito": "prefeita"}  # fmt: skip


def publicavel():
    return or_(PessoaVinculo.regra.in_(REGRAS_FORTES), PessoaVinculo.revisado.is_(True))


def _vinculos(session: Session, pessoa_id: int) -> list[PessoaVinculo]:
    return list(
        session.scalars(
            select(PessoaVinculo).where(PessoaVinculo.pessoa_id == pessoa_id, publicavel())
        )
    )


def _cargo(cargo: str, genero: str | None) -> str:
    texto = cargo.lower()
    if (genero or "").upper() == "FEMININO":
        for masc, fem in FEMININO.items():
            texto = texto.replace(masc, fem)
    return texto


def descricao_eleicao(c: Candidatura) -> str:
    eleito = "Eleita" if (c.genero or "").upper() == "FEMININO" else "Eleito"
    partido = f", pelo {c.partido}" if c.partido else ""
    lugar = ""
    if c.uf != "BR" and c.unidade:
        lugar = f" em {c.unidade}" + (f" ({c.uf})" if c.unidade != c.uf else "")
    return (
        f"{eleito} para {_cargo(c.cargo, c.genero)}{lugar} nas eleições de {c.ano_eleicao}{partido}"
    )


def data_eleicao(c: Candidatura) -> date | None:
    if c.data_eleicao:
        return c.data_eleicao
    return None if c.cargo in DOIS_TURNOS else PRIMEIRO_TURNO.get(c.ano_eleicao)


def _candidaturas(session: Session, vinculos: list[PessoaVinculo]) -> list[Candidatura]:
    chaves = [
        (int(ano), sq)
        for v in vinculos
        if v.fonte == "candidatura"
        for ano, sq in [v.id_externo.split(":", 1)]
    ]
    if not chaves:
        return []
    return list(
        session.scalars(
            select(Candidatura).where(
                tuple_(Candidatura.ano_eleicao, Candidatura.sq_candidato).in_(chaves)
            )
        )
    )


def pessoa(session: Session, pessoa_id: int) -> dict | None:
    registro = session.get(Pessoa, pessoa_id)
    if registro is None:
        return None
    vinculos = _vinculos(session, pessoa_id)
    perfis = []
    for v in vinculos:
        if v.fonte == "parlamentar":
            casa, id_externo = v.id_externo.split(":", 1)
            p = session.scalar(
                select(Parlamentar).where(
                    Parlamentar.casa == casa, Parlamentar.id_externo == id_externo
                )
            )
            if p:
                cargo = "Deputado federal" if casa == "camara" else "Senador"
                perfis.append({"tipo": "parlamentar", "id": p.id, "descricao": cargo})
        elif v.fonte == "mandato_local":
            casa, uf, ibge, id_externo = v.id_externo.split(":", 3)
            municipio = (
                MandatoLocal.municipio_ibge == ibge
                if ibge
                else MandatoLocal.municipio_ibge.is_(None)
            )
            m = session.scalar(
                select(MandatoLocal).where(
                    MandatoLocal.casa == casa,
                    MandatoLocal.uf == uf,
                    municipio,
                    MandatoLocal.id_externo == id_externo,
                )
            )
            if m:
                tipo = "vereador" if casa == "camara" else "deputado_estadual"
                perfis.append({"tipo": tipo, "id": m.id, "descricao": "Mandato atual na casa"})
    for c in sorted(_candidaturas(session, vinculos), key=lambda c: -c.ano_eleicao):
        perfis.append(
            {"tipo": "candidatura", "id": c.id, "descricao": f"{c.cargo.title()} ({c.ano_eleicao})"}
        )
    return {"id": registro.id, "nome": registro.nome, "perfis": perfis}


def eventos(
    session: Session,
    pessoa_id: int,
    tipo: str | None = None,
    de: date | None = None,
    ate: date | None = None,
) -> dict | None:
    """Linha do tempo: os eventos gravados (sanções, processos...) e as eleições, montadas
    na hora das candidaturas ligadas. Mais recentes primeiro; sem data, no fim."""
    if session.get(Pessoa, pessoa_id) is None:
        return None
    vinculos = _vinculos(session, pessoa_id)
    itens = []
    for c in _candidaturas(session, vinculos):
        if (c.situacao_turno or "").startswith("ELEITO"):
            itens.append(
                {
                    "data": data_eleicao(c),
                    "tipo": "eleito",
                    "descricao": descricao_eleicao(c),
                    "orgao": "TSE",
                    "numero_processo": None,
                    "situacao": c.situacao_turno,
                    "fonte_url": tse.URL_CANDIDATOS.format(ano=c.ano_eleicao),
                }
            )
    gravados = session.scalars(
        select(Evento)
        .join(PessoaVinculo, PessoaVinculo.id == Evento.vinculo_id)
        .where(Evento.pessoa_id == pessoa_id, publicavel())
    )
    for e in gravados:
        itens.append(
            {
                "data": e.data,
                "tipo": e.tipo,
                "descricao": e.descricao,
                "orgao": e.orgao,
                "numero_processo": e.numero_processo,
                "situacao": e.situacao,
                "fonte_url": e.fonte_url,
            }
        )
    itens = [
        i
        for i in itens
        if (tipo is None or i["tipo"] == tipo)
        and (de is None or (i["data"] and i["data"] >= de))
        and (ate is None or (i["data"] and i["data"] <= ate))
    ]
    itens.sort(key=lambda i: (i["data"] is not None, i["data"] or date.min), reverse=True)
    numeros = {i["numero_processo"] for i in itens if i["numero_processo"]}
    processos = {
        p.numero: p
        for p in session.scalars(select(Processo).where(Processo.numero.in_(numeros)))
    } if numeros else {}  # fmt: skip
    for i in itens:
        i["processo"] = _processo(processos.get(i["numero_processo"]))
    return {"pessoa_id": pessoa_id, "itens": itens}


def _processo(p: Processo | None) -> dict | None:
    """Situação do processo no DataJud. Sob sigilo, só a informação de que é sigiloso."""
    if p is None or not p.encontrado:
        return None
    if p.sigiloso:
        return {"tribunal": p.tribunal, "sigiloso": True, "classe": None, "orgao_julgador": None,
                "data_ajuizamento": None, "ultimo_andamento": None,
                "data_ultimo_andamento": None, "consultado_em": p.consultado_em}  # fmt: skip
    return {
        "tribunal": p.tribunal,
        "sigiloso": False,
        "classe": p.classe,
        "orgao_julgador": p.orgao_julgador,
        "data_ajuizamento": p.data_ajuizamento,
        "ultimo_andamento": p.ultimo_andamento,
        "data_ultimo_andamento": p.data_ultimo_andamento,
        "consultado_em": p.consultado_em,
    }


def casos(session: Session) -> list[dict]:
    contagem = dict(
        session.execute(
            select(Evento.caso_slug, func.count(func.distinct(Evento.pessoa_id)))
            .where(Evento.caso_slug.is_not(None))
            .group_by(Evento.caso_slug)
        ).all()
    )
    return [
        {"slug": c.slug, "nome": c.nome, "periodo": c.periodo, "pessoas": contagem.get(c.slug, 0)}
        for c in session.scalars(select(Caso).order_by(Caso.nome))
    ]


def caso(session: Session, slug: str) -> dict | None:
    registro = session.get(Caso, slug)
    if registro is None:
        return None
    documentos = session.scalars(
        select(CasoDocumento).where(CasoDocumento.caso_slug == slug).order_by(CasoDocumento.data)
    )
    participacoes = session.execute(
        select(Evento, Pessoa.nome)
        .join(Pessoa, Pessoa.id == Evento.pessoa_id)
        .join(PessoaVinculo, PessoaVinculo.id == Evento.vinculo_id)
        .where(Evento.caso_slug == slug, publicavel())
        .order_by(Pessoa.nome, Evento.data)
    ).all()
    return {
        "slug": registro.slug,
        "nome": registro.nome,
        "periodo": registro.periodo,
        "resumo": registro.resumo,
        "conferido_em": registro.conferido_em,
        "documentos": [
            {
                "tipo": d.tipo,
                "orgao": d.orgao,
                "numero": d.numero,
                "data": d.data,
                "url": d.url,
                "resumo": d.resumo,
            }
            for d in documentos
        ],  # fmt: skip
        "pessoas": [
            {
                "pessoa_id": e.pessoa_id,
                "nome": nome,
                "papel": e.situacao,
                "data": e.data,
                "descricao": e.descricao,
                "fonte_url": e.fonte_url,
            }
            for e, nome in participacoes
        ],  # fmt: skip
    }

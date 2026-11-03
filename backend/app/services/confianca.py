"""Linhas de confiança do cabeçalho do perfil: quando o cadastro (nome, partido e cargo) foi
conferido com a fonte oficial, o fato oficial mais recente que temos da pessoa e quem tem
nome muito parecido (para não confundir uma pessoa com a outra).

Só lê o que já está no banco: uma consulta para a data da carga, uma ou duas para o último
registro e uma, pelo índice de trigramas de `pessoa.chave_nome`, para os nomes parecidos."""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    Discurso,
    Evento,
    FonteIngestao,
    MandatoLocal,
    Municipio,
    Parlamentar,
    Pessoa,
    PessoaVinculo,
    Votacao,
    Voto,
)
from app.services import camaras, pessoas, tse
from app.services.busca import CARGO_LEGIVEL, FONTES_COM_PERFIL
from ingestion.comum import chave_nome

SIMILARIDADE_MINIMA = 0.8
LIMITE_PARECIDOS = 2
FONTES_CADASTRO = {
    "camara": ("camara_deputados", "Dados Abertos da Câmara dos Deputados"),
    "senado": ("senado_senadores", "Dados Abertos do Senado Federal"),
    "candidatura": ("tse_candidaturas", "Dados Abertos do TSE (candidaturas)"),
}
ROTAS = {
    "vereador": "vereador",
    "deputado_estadual": "deputado-estadual",
}


def _conferido_em(session: Session, fonte: str) -> date | None:
    momento: datetime | None = session.scalar(
        select(
            func.max(func.coalesce(FonteIngestao.concluido_em, FonteIngestao.iniciado_em))
        ).where(FonteIngestao.fonte == fonte, FonteIngestao.status == "ok")
    )
    return momento.astimezone().date() if momento else None


def _lugar_do_municipio(session: Session, ibge: str | None, uf: str) -> str:
    nome = session.scalar(select(Municipio.nome).where(Municipio.ibge == ibge)) if ibge else None
    return f"{nome}/{uf}" if nome else uf


def _descrever_candidatura(c: Candidatura) -> dict:
    municipal = c.cargo in ("PREFEITO", "VICE-PREFEITO", "VEREADOR")
    return {
        "cargo": CARGO_LEGIVEL.get(c.cargo, c.cargo.capitalize()),
        "lugar": f"{c.unidade}/{c.uf}" if municipal else c.uf,
        "href": f"/eleito/{c.id}",
    }


def _perfil_de(session: Session, tipo: str, perfil_id: int) -> dict | None:
    """Cargo, lugar e rota do perfil, na mesma linguagem para o próprio e os parecidos."""
    if tipo == "parlamentar":
        p = session.get(Parlamentar, perfil_id)
        if p is None:
            return None
        cargo = "Deputado federal" if p.casa == "camara" else "Senador"
        return {"cargo": cargo, "lugar": p.uf, "href": f"/parlamentar/{p.id}"}
    if tipo in ("vereador", "deputado_estadual"):
        m = session.get(MandatoLocal, perfil_id)
        if m is None:
            return None
        if m.casa == "camara":
            cargo, lugar = "Vereador", _lugar_do_municipio(session, m.municipio_ibge, m.uf)
        else:
            cargo, lugar = "Deputado estadual", m.uf
        return {"cargo": cargo, "lugar": lugar, "href": f"/{ROTAS[tipo]}/{m.id}"}
    c = session.get(Candidatura, perfil_id)
    return _descrever_candidatura(c) if c else None


def _fonte_de_cadastro(session: Session, tipo: str, perfil_id: int) -> tuple[str, str] | None:
    if tipo == "parlamentar":
        p = session.get(Parlamentar, perfil_id)
        return FONTES_CADASTRO[p.casa] if p else None
    if tipo in ("vereador", "deputado_estadual"):
        m = session.get(MandatoLocal, perfil_id)
        return camaras._fonte(m.casa, m.uf) if m else None
    return FONTES_CADASTRO["candidatura"]


def _ultimo_registro(
    session: Session, tipo: str, perfil_id: int, pessoa_id: int | None
) -> dict | None:
    candidatos: list[tuple[date, str]] = []
    if tipo == "parlamentar":
        p = session.get(Parlamentar, perfil_id)
        if p is not None:
            discurso = session.scalar(
                select(func.max(Discurso.data)).where(Discurso.parlamentar_id == p.id)
            )
            if discurso:
                candidatos.append((discurso, "discurso em plenário"))
            if p.casa == "camara":  # no Senado o voto inclui as ausências: fica de fora
                voto = session.scalar(
                    select(func.max(Votacao.data))
                    .join(Voto, Voto.votacao_id == Votacao.id)
                    .where(Voto.parlamentar_id == p.id)
                )
                if voto:
                    candidatos.append((voto, "voto em plenário"))
    if pessoa_id is not None:
        evento = session.scalar(
            select(func.max(Evento.data))
            .join(PessoaVinculo, PessoaVinculo.id == Evento.vinculo_id)
            .where(Evento.pessoa_id == pessoa_id, Evento.data <= date.today(), pessoas.publicavel())
        )
        if evento:
            candidatos.append((evento, "fato na linha do tempo"))
    if not candidatos:
        return None
    data, nome = max(candidatos)
    return {"tipo": nome, "data": data}


def _chave_do_perfil(session: Session, tipo: str, perfil_id: int, pessoa_id: int | None) -> str:
    if pessoa_id is not None:
        return session.get(Pessoa, pessoa_id).chave_nome
    if tipo == "parlamentar":
        p = session.get(Parlamentar, perfil_id)
        return chave_nome(p.nome_civil or p.nome_parlamentar)
    if tipo in ("vereador", "deputado_estadual"):
        m = session.get(MandatoLocal, perfil_id)
        return chave_nome(m.nome_completo or m.nome)
    return chave_nome(session.get(Candidatura, perfil_id).nome)


def _perfil_da_pessoa(session: Session, pessoa_id: int, nome: str) -> dict | None:
    """O perfil mais relevante da pessoa (mandato atual antes de candidatura recente)."""
    melhores: list[tuple[int, dict]] = []
    for v in pessoas._vinculos(session, pessoa_id):
        if v.fonte not in FONTES_COM_PERFIL:
            continue
        perfil, ordem = None, 0
        if v.fonte == "parlamentar":
            casa, id_externo = v.id_externo.split(":", 1)
            p = session.scalar(
                select(Parlamentar).where(
                    Parlamentar.casa == casa, Parlamentar.id_externo == id_externo
                )
            )
            perfil = _perfil_de(session, "parlamentar", p.id) if p else None
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
            tipo = "vereador" if casa == "camara" else "deputado_estadual"
            perfil, ordem = (_perfil_de(session, tipo, m.id) if m else None), 1
        else:
            ano, sq = v.id_externo.split(":", 1)
            c = session.scalar(
                select(Candidatura).where(
                    Candidatura.ano_eleicao == int(ano),
                    Candidatura.sq_candidato == sq,
                    Candidatura.cargo.in_(tse.CARGOS_COM_PERFIL),
                )
            )
            if c:
                perfil, ordem = _descrever_candidatura(c), 2 + 3000 - c.ano_eleicao
        if perfil:
            melhores.append((ordem, perfil))
    if not melhores:
        return None
    return {"nome": nome, **min(melhores, key=lambda x: x[0])[1]}


def _parecidos(session: Session, chave: str, pessoa_id: int | None, proprio: dict) -> list[dict]:
    """Outras pessoas públicas com nome igual (normalizado) ou quase, em outro cargo ou lugar."""
    if len(chave) < 6:
        return []
    similar = func.similarity(Pessoa.chave_nome, chave)
    candidatas = session.execute(
        select(Pessoa.id, Pessoa.nome)
        .where(Pessoa.chave_nome.op("%")(chave), similar >= SIMILARIDADE_MINIMA)
        .order_by(similar.desc(), Pessoa.id)
        .limit(12)
    ).all()
    achados = []
    for outra_id, nome in candidatas:
        if outra_id == pessoa_id:
            continue
        perfil = _perfil_da_pessoa(session, outra_id, nome)
        if perfil is None or (perfil["cargo"], perfil["lugar"]) == (
            proprio["cargo"],
            proprio["lugar"],
        ):
            continue
        achados.append(perfil)
        if len(achados) == LIMITE_PARECIDOS:
            break
    return achados


def do_perfil(session: Session, tipo: str, perfil_id: int) -> dict | None:
    """None se o perfil não existe."""
    fonte = _fonte_de_cadastro(session, tipo, perfil_id)
    proprio = _perfil_de(session, tipo, perfil_id)
    if fonte is None or proprio is None:
        return None
    pessoa_id = pessoas.pessoa_de(session, tipo, perfil_id)
    chave = _chave_do_perfil(session, tipo, perfil_id, pessoa_id)
    return {
        "conferido_em": _conferido_em(session, fonte[0]),
        "fonte": fonte[1],
        "ultimo_registro": _ultimo_registro(session, tipo, perfil_id, pessoa_id),
        "parecidos": _parecidos(session, chave, pessoa_id, proprio),
    }

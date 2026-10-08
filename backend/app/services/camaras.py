"""Câmaras municipais e assembleias com dados da própria casa (SAPL): quem está no cargo
hoje."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.models import (
    Candidatura,
    FonteIngestao,
    Foto,
    GastoLocal,
    MandatoLocal,
    ProjetoLocal,
    VotacaoLocal,
    VotoLocal,
)
from app.services import tse

FONTES = {
    "camara": ("sapl_camaras", "Sistema legislativo da câmara (SAPL)"),
    "assembleia": ("sapl_assembleias", "Sistema legislativo da assembleia (SAPL)"),
}
# Assembleias com conector próprio (não usam o SAPL).
FONTES_PROPRIAS = {
    "MG": ("almg", "Dados abertos da Assembleia de Minas Gerais (ALMG)"),
    "SP": ("alesp", "Dados abertos da Assembleia de São Paulo (ALESP)"),
}


def _fonte(casa: str, uf: str) -> tuple[str, str]:
    if casa == "assembleia" and uf in FONTES_PROPRIAS:
        return FONTES_PROPRIAS[uf]
    return FONTES[casa]


def _atualizado_em(session: Session, casa: str, uf: str = "") -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == _fonte(casa, uf)[0], FonteIngestao.status == "ok"
        )
    )


POR_PAGINA = 20
# Registros de voto que não são voto: a pessoa estava na lista mas não votou.
NAO_VOTOU = ("não votou", "nao votou", "ausente")


def _votou() -> Any:
    return func.lower(VotoLocal.voto).not_in(NAO_VOTOU)


def _da_mesma_casa(m: MandatoLocal) -> Any:
    if m.casa == "camara":
        return MandatoLocal.municipio_ibge == m.municipio_ibge
    return (MandatoLocal.casa == "assembleia") & (MandatoLocal.uf == m.uf)


def _contar_votos(session: Session, ids: list[int]) -> dict[int, int]:
    return dict(
        session.execute(
            select(VotoLocal.mandato_id, func.count())
            .where(VotoLocal.mandato_id.in_(ids), _votou())
            .group_by(VotoLocal.mandato_id)
        ).all()
    )


def presenca(session: Session, m: MandatoLocal) -> dict | None:
    """Sessões com presença registrada durante o mandato, e a média da casa: a média do
    percentual de presença entre quem está em exercício (quem não tem sessão no período
    não entra, porque não havia como estar presente)."""
    if not m.sessoes:
        return None
    colegas = session.execute(
        select(MandatoLocal.sessoes, MandatoLocal.presencas).where(
            _da_mesma_casa(m), MandatoLocal.em_exercicio, MandatoLocal.sessoes > 0
        )
    ).all()
    percentuais = [100 * (p or 0) / s for s, p in colegas]
    return {
        "sessoes": m.sessoes,
        "presencas": m.presencas or 0,
        "media_casa": round(sum(percentuais) / len(percentuais), 1) if percentuais else None,
    }


def gastos(session: Session, m: MandatoLocal) -> dict | None:
    """Gastos do gabinete no ano mais recente com dados, por categoria, e a média da casa
    (entre quem está em exercício; quem não gastou nada entra com zero)."""
    ano = session.scalar(select(func.max(GastoLocal.ano)).where(GastoLocal.mandato_id == m.id))
    if ano is None:
        return None
    categorias = session.execute(
        select(GastoLocal.categoria, func.sum(GastoLocal.valor))
        .where(GastoLocal.mandato_id == m.id, GastoLocal.ano == ano)
        .group_by(GastoLocal.categoria)
        .order_by(func.sum(GastoLocal.valor).desc())
    ).all()
    meses = session.scalar(
        select(func.max(GastoLocal.mes)).where(GastoLocal.mandato_id == m.id, GastoLocal.ano == ano)
    )
    colegas = session.scalars(
        select(MandatoLocal.id).where(_da_mesma_casa(m), MandatoLocal.em_exercicio)
    ).all()
    soma_casa = session.scalar(
        select(func.coalesce(func.sum(GastoLocal.valor), 0)).where(
            GastoLocal.mandato_id.in_(colegas), GastoLocal.ano == ano
        )
    )
    return {
        "ano": ano,
        "ate_mes": meses,
        "total": sum((v for _, v in categorias), Decimal(0)),
        "media_casa": soma_casa / len(colegas) if colegas else None,
        "por_categoria": [{"categoria": c, "valor": v} for c, v in categorias],
    }


def votacoes(session: Session, m: MandatoLocal, pagina: int = 1) -> dict:
    """Como votou nas votações nominais da casa, das mais recentes para as mais antigas."""
    total = session.scalar(select(func.count()).where(VotoLocal.mandato_id == m.id)) or 0
    votou = session.scalar(select(func.count()).where(VotoLocal.mandato_id == m.id, _votou())) or 0
    linhas = session.execute(
        select(VotacaoLocal, VotoLocal.voto)
        .join(VotoLocal, VotoLocal.votacao_id == VotacaoLocal.id)
        .where(VotoLocal.mandato_id == m.id)
        .order_by(VotacaoLocal.data.desc().nulls_last(), VotacaoLocal.id.desc())
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    ).all()
    da_casa = session.scalar(
        select(func.count())
        .select_from(VotacaoLocal)
        .where(
            VotacaoLocal.municipio_ibge == m.municipio_ibge
            if m.casa == "camara"
            else (VotacaoLocal.casa == "assembleia") & (VotacaoLocal.uf == m.uf)
        )
    )
    return {
        "casa_registra": bool(da_casa),
        "total": total,
        "votou": votou,
        "pagina": pagina,
        "por_pagina": POR_PAGINA,
        "itens": [
            {
                "data": v.data,
                "materia": v.materia,
                "resultado": v.resultado,
                "sim": v.sim,
                "nao": v.nao,
                "abstencoes": v.abstencoes,
                "voto": voto,
                "url": v.url,
            }
            for v, voto in linhas
        ],
        "fonte_nome": _fonte(m.casa, m.uf)[1],
        "fonte_url": m.sapl_url,
        "atualizado_em": _atualizado_em(session, m.casa, m.uf),
    }


def _item(m: MandatoLocal, projetos: int, com_foto_tse: set[int], votos: int = 0) -> dict:
    return {
        "sessoes": m.sessoes,
        "presencas": m.presencas,
        "votacoes": votos,
        "id": m.id,
        "nome": m.nome,
        "partido": m.partido,
        "foto_url": m.foto_url,
        "foto_tse": m.candidatura_id in com_foto_tse if m.candidatura_id else False,
        "titular": m.titular,
        "em_exercicio": m.em_exercicio,
        "candidatura_id": m.candidatura_id,
        "proposicoes": sum(m.proposicoes_por_tipo.values()),
        "projetos": projetos,
    }


def camara(session: Session, ibge: str) -> dict | None:
    return _casa(session, "camara", MandatoLocal.municipio_ibge == ibge)


def assembleia(session: Session, uf: str) -> dict | None:
    return _casa(
        session, "assembleia", (MandatoLocal.casa == "assembleia") & (MandatoLocal.uf == uf)
    )


def _casa(session: Session, casa: str, filtro: Any) -> dict | None:
    mandatos = session.scalars(
        select(MandatoLocal).where(filtro, MandatoLocal.em_exercicio).order_by(MandatoLocal.nome)
    ).all()
    if not mandatos:
        return None
    projetos = dict(
        session.execute(
            select(ProjetoLocal.mandato_id, func.count())
            .where(ProjetoLocal.mandato_id.in_([m.id for m in mandatos]))
            .group_by(ProjetoLocal.mandato_id)
        ).all()
    )
    votos = _contar_votos(session, [m.id for m in mandatos])
    candidaturas = [m.candidatura_id for m in mandatos if m.candidatura_id]
    com_foto = set(
        session.scalars(select(Foto.candidatura_id).where(Foto.candidatura_id.in_(candidaturas)))
    )
    return {
        "sapl_url": mandatos[0].sapl_url,
        "itens": [_item(m, projetos.get(m.id, 0), com_foto, votos.get(m.id, 0)) for m in mandatos],
        "fonte_nome": _fonte(casa, mandatos[0].uf)[1],
        "fonte_url": mandatos[0].sapl_url,
        "atualizado_em": _atualizado_em(session, casa, mandatos[0].uf),
    }


def vereador(session: Session, mandato: MandatoLocal) -> dict:
    projetos = session.scalars(
        select(ProjetoLocal)
        .where(ProjetoLocal.mandato_id == mandato.id)
        .order_by(ProjetoLocal.data_apresentacao.desc().nulls_last())
    ).all()
    com_foto = (
        set(
            session.scalars(
                select(Foto.candidatura_id).where(Foto.candidatura_id == mandato.candidatura_id)
            )
        )
        if mandato.candidatura_id
        else set()
    )
    return {
        **_item(
            mandato,
            len(projetos),
            com_foto,
            _contar_votos(session, [mandato.id]).get(mandato.id, 0),
        ),
        "presenca": presenca(session, mandato),
        "gastos": gastos(session, mandato),
        "casa": mandato.casa,
        "uf": mandato.uf,
        "municipio_ibge": mandato.municipio_ibge,
        "nome_completo": mandato.nome_completo,
        "email": mandato.email,
        "telefone": mandato.telefone,
        "inicio": mandato.inicio,
        "fim": mandato.fim,
        "proposicoes_por_tipo": [
            {"tipo": tipo, "total": total}
            for tipo, total in sorted(
                mandato.proposicoes_por_tipo.items(), key=lambda item: item[1], reverse=True
            )
        ],
        "lista_projetos": [
            {
                "tipo": p.tipo,
                "numero": p.numero,
                "ano": p.ano,
                "ementa": p.ementa,
                "data_apresentacao": p.data_apresentacao,
                "em_tramitacao": p.em_tramitacao,
                "primeiro_autor": p.primeiro_autor,
                "url": p.url,
            }
            for p in projetos
        ],
        "sapl_url": mandato.sapl_url,
        "fonte_nome": _fonte(mandato.casa, mandato.uf)[1],
        "fonte_url": mandato.sapl_url,
        "atualizado_em": _atualizado_em(session, mandato.casa, mandato.uf),
    }


def mesma_casa(a: MandatoLocal, b: MandatoLocal) -> bool:
    if a.casa != b.casa:
        return False
    return a.municipio_ibge == b.municipio_ibge if a.casa == "camara" else a.uf == b.uf


def _lado(session: Session, m: MandatoLocal) -> dict:
    projetos = session.scalar(select(func.count()).where(ProjetoLocal.mandato_id == m.id)) or 0
    candidatura = session.get(Candidatura, m.candidatura_id) if m.candidatura_id else None
    com_foto = (
        set(
            session.scalars(
                select(Foto.candidatura_id).where(Foto.candidatura_id == m.candidatura_id)
            )
        )
        if m.candidatura_id
        else set()
    )
    return {
        **_item(m, projetos, com_foto, _contar_votos(session, [m.id]).get(m.id, 0)),
        "presenca": presenca(session, m),
        "proposicoes_por_tipo": m.proposicoes_por_tipo,
        "pessoais": tse._pessoais(session, [candidatura]) if candidatura else None,
        "votos_recebidos": candidatura.votos if candidatura else None,
    }


def comparar(session: Session, a: MandatoLocal, b: MandatoLocal) -> dict:
    """Dois parlamentares da mesma casa lado a lado e as votações nominais em que os dois
    registraram voto: em quantas votaram igual e onde divergiram."""
    va, vb = aliased(VotoLocal), aliased(VotoLocal)
    pares = session.execute(
        select(VotacaoLocal, va.voto, vb.voto)
        .join(va, va.votacao_id == VotacaoLocal.id)
        .join(vb, vb.votacao_id == VotacaoLocal.id)
        .where(
            va.mandato_id == a.id,
            vb.mandato_id == b.id,
            func.lower(va.voto).not_in(NAO_VOTOU),
            func.lower(vb.voto).not_in(NAO_VOTOU),
        )
        .order_by(VotacaoLocal.data.desc().nulls_last(), VotacaoLocal.id.desc())
    ).all()
    divergencias = [(v, x, y) for v, x, y in pares if x != y]
    tipos = sorted(set(a.proposicoes_por_tipo) | set(b.proposicoes_por_tipo))
    return {
        "casa": a.casa,
        "a": _lado(session, a),
        "b": _lado(session, b),
        "proposicoes_por_tipo": [
            {
                "tipo": t,
                "a": a.proposicoes_por_tipo.get(t, 0),
                "b": b.proposicoes_por_tipo.get(t, 0),
            }
            for t in tipos
        ],
        "votacoes_em_comum": len(pares),
        "iguais": len(pares) - len(divergencias),
        "divergencias": [
            {
                "data": v.data,
                "materia": v.materia,
                "resultado": v.resultado,
                "url": v.url,
                "voto_a": x,
                "voto_b": y,
            }
            for v, x, y in divergencias[:20]
        ],  # fmt: skip
        "fonte_nome": _fonte(a.casa, a.uf)[1],
        "fonte_url": a.sapl_url,
        "atualizado_em": _atualizado_em(session, a.casa, a.uf),
    }

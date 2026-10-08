"""Câmaras municipais e assembleias com dados da própria casa (SAPL): quem está no cargo
hoje."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Foto, MandatoLocal, ProjetoLocal, VotacaoLocal, VotoLocal

FONTES = {
    "camara": ("sapl_camaras", "Sistema legislativo da câmara (SAPL)"),
    "assembleia": ("sapl_assembleias", "Sistema legislativo da assembleia (SAPL)"),
}


def _atualizado_em(session: Session, casa: str) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTES[casa][0], FonteIngestao.status == "ok"
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
        "fonte_nome": FONTES[m.casa][1],
        "fonte_url": m.sapl_url,
        "atualizado_em": _atualizado_em(session, m.casa),
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
        "fonte_nome": FONTES[casa][1],
        "fonte_url": mandatos[0].sapl_url,
        "atualizado_em": _atualizado_em(session, casa),
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
        "fonte_nome": FONTES[mandato.casa][1],
        "fonte_url": mandato.sapl_url,
        "atualizado_em": _atualizado_em(session, mandato.casa),
    }

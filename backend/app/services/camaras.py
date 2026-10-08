"""Câmaras municipais e assembleias com dados da própria casa (SAPL): quem está no cargo
hoje."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Foto, MandatoLocal, ProjetoLocal

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


def _item(m: MandatoLocal, projetos: int, com_foto_tse: set[int]) -> dict:
    return {
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
    candidaturas = [m.candidatura_id for m in mandatos if m.candidatura_id]
    com_foto = set(
        session.scalars(select(Foto.candidatura_id).where(Foto.candidatura_id.in_(candidaturas)))
    )
    return {
        "sapl_url": mandatos[0].sapl_url,
        "itens": [_item(m, projetos.get(m.id, 0), com_foto) for m in mandatos],
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
        **_item(mandato, len(projetos), com_foto),
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

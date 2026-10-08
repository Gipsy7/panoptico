"""Câmaras municipais com dados da própria câmara (SAPL): quem está no cargo hoje."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, Foto, MandatoLocal, ProjetoLocal


def _atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == "sapl_camaras", FonteIngestao.status == "ok"
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
    mandatos = session.scalars(
        select(MandatoLocal)
        .where(MandatoLocal.municipio_ibge == ibge, MandatoLocal.em_exercicio)
        .order_by(MandatoLocal.nome)
    ).all()
    if not mandatos:
        return None
    projetos = dict(
        session.execute(
            select(ProjetoLocal.mandato_id, func.count())
            .where(ProjetoLocal.municipio_ibge == ibge)
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
        "fonte_nome": "Sistema legislativo da câmara (SAPL)",
        "fonte_url": mandatos[0].sapl_url,
        "atualizado_em": _atualizado_em(session),
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
        "fonte_nome": "Sistema legislativo da câmara (SAPL)",
        "fonte_url": mandato.sapl_url,
        "atualizado_em": _atualizado_em(session),
    }

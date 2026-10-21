"""Votação e projeto de câmara municipal ou assembleia: o que a própria casa publica.

Casas locais publicam matéria, resultado, placar e o voto de cada parlamentar; não há orientação
de bancada nem discursos nesse formato aberto, e a resposta diz isso (`sem_orientacao`,
`sem_discursos`). A ementa só aparece quando a casa publica (docs/DECISOES.md, 2026-10-21)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MandatoLocal, Municipio, ProjetoLocal, VotacaoLocal, VotoLocal
from app.services import projeto_fontes

CASA_DO_LOCAL = {"assembleia": "assembleia", "camara": "camara_municipal"}
AVISO = (
    "A casa publica o resultado e o voto de cada parlamentar, mas não publica orientação de "
    "bancada nem discursos neste formato aberto."
)
AVISO_SEM_EMENTA = " A casa não publica a ementa da matéria votada nesta votação."
ORDEM_VOTO = {"Sim": 0, "Não": 1}


def _nome_municipio(session: Session, ibge: str | None) -> str | None:
    if not ibge:
        return None
    return session.scalar(select(Municipio.nome).where(Municipio.ibge == ibge))


def votacao(session: Session, votacao_id: int) -> dict | None:
    v = session.get(VotacaoLocal, votacao_id)
    if v is None:
        return None
    votos = [
        {"mandato_id": mid, "nome": nome, "partido": partido, "voto": voto}
        for mid, nome, partido, voto in session.execute(
            select(MandatoLocal.id, MandatoLocal.nome, MandatoLocal.partido, VotoLocal.voto)
            .join(VotoLocal, VotoLocal.mandato_id == MandatoLocal.id)
            .where(VotoLocal.votacao_id == v.id)
        )
    ]
    votos.sort(key=lambda x: (ORDEM_VOTO.get(x["voto"], 2), x["voto"], x["nome"], x["mandato_id"]))
    return {
        "id": v.id,
        "casa": CASA_DO_LOCAL.get(v.casa, v.casa),
        "uf": v.uf,
        "municipio_ibge": v.municipio_ibge,
        "municipio": _nome_municipio(session, v.municipio_ibge),
        "data": v.data,
        "materia": v.materia,
        "ementa": v.materia_ementa,
        "resultado": v.resultado,
        "sim": v.sim,
        "nao": v.nao,
        "abstencoes": v.abstencoes,
        "votos": votos,
        "projeto_local_id": v.projeto_local_id,
        "projeto_link": f"/projeto/local/{v.projeto_local_id}" if v.projeto_local_id else None,
        "url_oficial": v.url,
        "sem_orientacao": True,
        "sem_discursos": True,
        "aviso": AVISO + ("" if v.materia_ementa else AVISO_SEM_EMENTA),
        **projeto_fontes.fonte_local(session, v.url),
    }


def projeto(session: Session, projeto_id: int) -> dict | None:
    p = session.get(ProjetoLocal, projeto_id)
    if p is None:
        return None
    mandato = session.get(MandatoLocal, p.mandato_id)
    votacoes = session.scalars(
        select(VotacaoLocal)
        .where(VotacaoLocal.projeto_local_id == p.id)
        .order_by(VotacaoLocal.data.desc().nullslast(), VotacaoLocal.id.desc())
    ).all()
    numero = f" nº {p.numero}" if p.numero is not None else ""
    return {
        "id": p.id,
        "rotulo": f"{p.tipo}{numero}/{p.ano}",
        "tipo": p.tipo,
        "numero": p.numero,
        "ano": p.ano,
        "ementa": p.ementa,
        "data_apresentacao": p.data_apresentacao,
        "em_tramitacao": p.em_tramitacao,
        "casa": CASA_DO_LOCAL.get(mandato.casa, mandato.casa) if mandato else "camara_municipal",
        "uf": mandato.uf if mandato else None,
        "municipio_ibge": p.municipio_ibge,
        "municipio": _nome_municipio(session, p.municipio_ibge),
        "autor": {"mandato_id": mandato.id, "nome": mandato.nome, "partido": mandato.partido}
        if mandato
        else None,
        "votacoes": [
            {
                "id": v.id,
                "data": v.data,
                "materia": v.materia,
                "resultado": v.resultado,
                "sim": v.sim,
                "nao": v.nao,
                "abstencoes": v.abstencoes,
                "link": f"/votacoes/local/{v.id}",
            }
            for v in votacoes
        ],
        "url_oficial": p.url,
        "sem_orientacao": True,
        "sem_discursos": True,
        "aviso": AVISO
        + (
            ""
            if votacoes
            else " Este projeto não tem votação nominal registrada nesta fonte; pode ter sido "
            "votado de forma simbólica, que não registra o voto de cada um."
        ),
        **projeto_fontes.fonte_local(session, p.url),
    }

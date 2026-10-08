"""Busca por nome em todos os níveis: parlamentares federais, eleitos do TSE (presidente,
governadores, prefeitos, deputados estaduais, vereadores) e quem está no cargo hoje nas
câmaras e assembleias com SAPL.

Cada pessoa aparece uma vez: um eleito que a própria casa já lista como no cargo aparece
pelo dado da casa, que é o atual."""

from typing import Any

from sqlalchemy import and_, case, func, select, tuple_
from sqlalchemy.orm import Session

from app.models import Candidatura, MandatoLocal, Municipio, Parlamentar
from ingestion.comum import chave_nome

LIMITE = 20
ACENTOS = "ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇÑ.-'"
SEM_ACENTO = "AAAAAEEEEIIIIOOOOOUUUUCN   "
# Cargos que vêm de outra fonte (parlamentares federais e seus suplentes).
FEDERAIS = ("DEPUTADO FEDERAL", "SENADOR", "1º SUPLENTE", "2º SUPLENTE")
ORDEM_CARGO = {
    "PRESIDENTE": 0,
    "VICE-PRESIDENTE": 1,
    "GOVERNADOR": 2,
    "VICE-GOVERNADOR": 3,
    "DEPUTADO ESTADUAL": 5,
    "DEPUTADO DISTRITAL": 5,
    "PREFEITO": 6,
    "VICE-PREFEITO": 7,
    "VEREADOR": 8,
}
CARGO_LEGIVEL = {
    "PRESIDENTE": "Presidente",
    "VICE-PRESIDENTE": "Vice-presidente",
    "GOVERNADOR": "Governador",
    "VICE-GOVERNADOR": "Vice-governador",
    "DEPUTADO ESTADUAL": "Deputado estadual",
    "DEPUTADO DISTRITAL": "Deputado distrital",
    "PREFEITO": "Prefeito",
    "VICE-PREFEITO": "Vice-prefeito",
    "VEREADOR": "Vereador",
}


def _casa(coluna: Any, palavras: list[str]) -> Any:
    """Todas as palavras aparecem no nome, sem diferença de acento ou maiúscula."""
    normal = func.translate(func.upper(coluna), ACENTOS, SEM_ACENTO)
    return and_(*(normal.like(f"%{p}%") for p in palavras))


def buscar(session: Session, nome: str) -> list[dict]:
    palavras = chave_nome(nome).split()
    if not palavras or sum(len(p) for p in palavras) < 3:
        return []
    resultado: list[dict] = []

    federais = session.scalars(
        select(Parlamentar)
        .where(Parlamentar.em_exercicio, _casa(Parlamentar.nome_parlamentar, palavras))
        .order_by(Parlamentar.nome_parlamentar)
        .limit(LIMITE)
    ).all()
    for p in federais:
        resultado.append(
            {
                "nome": p.nome_parlamentar,
                "nome_completo": p.nome_civil,
                "cargo": "Deputado federal" if p.casa == "camara" else "Senador",
                "partido": p.partido,
                "lugar": p.uf,
                "caminho": f"/parlamentar/{p.id}",
            }
        )

    mandatos = session.execute(
        select(MandatoLocal, Municipio.nome)
        .outerjoin(Municipio, Municipio.ibge == MandatoLocal.municipio_ibge)
        .where(
            MandatoLocal.em_exercicio,
            _casa(MandatoLocal.nome, palavras) | _casa(MandatoLocal.nome_completo, palavras),
        )
        .order_by(MandatoLocal.nome)
        .limit(LIMITE)
    ).all()
    ja_listados: set[int] = set()
    locais = []
    for m, cidade in mandatos:
        camara = m.casa == "camara"
        if m.candidatura_id:
            ja_listados.add(m.candidatura_id)
        locais.append(
            {
                "nome": m.nome,
                "nome_completo": m.nome_completo,
                "cargo": "Vereador"
                if camara
                else ("Deputado distrital" if m.uf == "DF" else "Deputado estadual"),
                "partido": m.partido,
                "lugar": f"{cidade}/{m.uf}" if cidade else m.uf,
                "caminho": f"/{'vereador' if camara else 'deputado-estadual'}/{m.id}",
                "_ordem": ORDEM_CARGO["VEREADOR" if camara else "DEPUTADO ESTADUAL"],
            }
        )

    eleito = Candidatura.situacao_turno.like("ELEITO%")
    ultima = (
        select(Candidatura.cargo, func.max(Candidatura.ano_eleicao))
        .where(eleito)
        .group_by(Candidatura.cargo)
    )
    candidaturas = session.scalars(
        select(Candidatura)
        .where(
            eleito,
            Candidatura.cargo.not_in(FEDERAIS),
            tuple_(Candidatura.cargo, Candidatura.ano_eleicao).in_(ultima),
            _casa(Candidatura.nome_urna, palavras) | _casa(Candidatura.nome, palavras),
        )
        .order_by(case(ORDEM_CARGO, value=Candidatura.cargo, else_=9), Candidatura.nome_urna)
        .limit(LIMITE * 2)
    ).all()
    for c in candidaturas:
        if c.id in ja_listados:
            continue
        municipal = c.cargo in ("PREFEITO", "VICE-PREFEITO", "VEREADOR")
        locais.append(
            {
                "nome": c.nome_urna,
                "nome_completo": c.nome,
                "cargo": CARGO_LEGIVEL.get(c.cargo, c.cargo.capitalize()),
                "partido": c.partido,
                "lugar": f"{c.unidade}/{c.uf}"
                if municipal
                else ("Brasil" if "PRESIDENTE" in c.cargo else c.uf),
                "caminho": f"/eleito/{c.id}",
                "_ordem": ORDEM_CARGO.get(c.cargo, 9),
            }
        )

    locais.sort(key=lambda x: (x["_ordem"], chave_nome(x["nome"])))
    for item in resultado + locais:
        item.pop("_ordem", None)
        # O nome completo só ajuda quando é diferente do nome de urna ou parlamentar.
        if chave_nome(item["nome_completo"]) == chave_nome(item["nome"]):
            item["nome_completo"] = None
    return (resultado + locais)[:LIMITE]

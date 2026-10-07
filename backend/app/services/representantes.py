from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Parlamentar

UFS = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}  # fmt: skip


@dataclass
class Representantes:
    deputados: list[Parlamentar]
    senadores: list[Parlamentar]
    atualizado_em: datetime | None


def listar_por_uf(session: Session, uf: str) -> Representantes:
    uf = uf.upper()
    filtro = (Parlamentar.uf == uf, Parlamentar.em_exercicio.is_(True))
    parlamentares = session.scalars(
        select(Parlamentar).where(*filtro).order_by(func.lower(Parlamentar.nome_parlamentar))
    ).all()
    atualizado_em = session.scalar(select(func.min(Parlamentar.atualizado_em)).where(*filtro))
    return Representantes(
        deputados=[p for p in parlamentares if p.casa == "camara"],
        senadores=[p for p in parlamentares if p.casa == "senado"],
        atualizado_em=atualizado_em,
    )

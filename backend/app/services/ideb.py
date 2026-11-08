"""IDEB de um município, com o do estado e o do Brasil na mesma rede, para comparar. A rede
de cada etapa é a que a oferece (anos iniciais e finais: municipal e estadual; ensino médio:
estadual); a rede pública (todas as públicas juntas) também vem."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, IdebResultado

FONTE = "inep_ideb"
FONTE_NOME = "INEP (Ideb, resultados da divulgação)"
FONTE_URL = "https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados"
ETAPAS = [
    ("iniciais", "Anos iniciais do fundamental (1º ao 5º ano)"),
    ("finais", "Anos finais do fundamental (6º ao 9º ano)"),
    ("medio", "Ensino médio"),
]
REDES = ["municipal", "estadual", "publica", "federal"]


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def do_municipio(session: Session, ibge: str, uf: str) -> dict:
    linhas = session.scalars(
        select(IdebResultado).where(
            or_(
                (IdebResultado.abrangencia == "municipio") & (IdebResultado.codigo == ibge),
                (IdebResultado.abrangencia == "uf") & (IdebResultado.codigo == uf),
                IdebResultado.abrangencia == "brasil",
            )
        )
    ).all()
    series: dict[tuple, list] = defaultdict(list)
    for r in sorted(linhas, key=lambda r: r.ano):
        series[(r.abrangencia, r.etapa, r.rede)].append({"ano": r.ano, "valor": float(r.valor)})
    etapas = []
    for etapa, rotulo in ETAPAS:
        redes = [
            {
                "rede": rede,
                "serie": series[("municipio", etapa, rede)],
                "uf": series.get(("uf", etapa, rede), []),
                "brasil": series.get(("brasil", etapa, rede), []),
            }
            for rede in REDES
            if series.get(("municipio", etapa, rede))
        ]
        if redes:
            etapas.append({"etapa": etapa, "rotulo": rotulo, "redes": redes})
    return {
        "municipio_ibge": ibge,
        "uf": uf,
        "etapas": etapas,
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }

"""Obras federais de um município (Obrasgov.br): quantas há em cada situação, o valor previsto
e a lista, com o percentual executado. Só fatos da fonte; a ordem segue a situação (as que
estão em andamento ou paradas primeiro) e o valor, não um juízo."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FonteIngestao, ObraFederal, ObraFederalMunicipio

FONTE = "obrasgov_obras"
FONTE_NOME = "Obrasgov.br (Ministério da Gestão e da Inovação)"
FONTE_URL = "https://api-publica.obrasgov.gestao.gov.br/obras"
URL_OBRA = FONTE_URL + "/projeto-investimento?id_projeto_investimento={id}"
ORDEM = ["Em execução", "Paralisada", "Inacabada", "Cadastrada", "Concluída", "Cancelada"]
LIMITE_ITENS = 300


def atualizado_em(session: Session) -> datetime | None:
    return session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == FONTE, FonteIngestao.status == "ok"
        )
    )


def _ordem(situacao: str | None) -> int:
    return ORDEM.index(situacao) if situacao in ORDEM else len(ORDEM)


def do_municipio(session: Session, ibge: str) -> dict:
    obras = session.scalars(
        select(ObraFederal)
        .join(ObraFederalMunicipio, ObraFederalMunicipio.obra_id == ObraFederal.id_unico)
        .where(ObraFederalMunicipio.municipio_ibge == ibge)
    ).all()
    por: dict[str, dict] = {}
    for o in obras:
        s = o.situacao or "Sem situação"
        g = por.setdefault(s, {"situacao": s, "obras": 0, "valor_previsto": Decimal(0)})
        g["obras"] += 1
        g["valor_previsto"] += o.valor_previsto or 0
    ordenadas = sorted(obras, key=lambda o: (_ordem(o.situacao), -(o.valor_previsto or 0)))
    return {
        "municipio_ibge": ibge,
        "total": len(obras),
        "valor_previsto": sum((o.valor_previsto or Decimal(0) for o in obras), Decimal(0)),
        "por_situacao": sorted(por.values(), key=lambda g: _ordem(g["situacao"])),
        "itens": [
            {
                "id_unico": o.id_unico,
                "nome": o.nome,
                "situacao": o.situacao,
                "tipo": o.tipo,
                "valor_previsto": o.valor_previsto,
                "percentual_execucao": o.percentual_execucao,
                "data_inicial_prevista": o.data_inicial_prevista,
                "data_final_prevista": o.data_final_prevista,
                "executor": o.executor,
                "responsavel": o.responsavel,
                "url": URL_OBRA.format(id=o.id_unico),
            }
            for o in ordenadas[:LIMITE_ITENS]
        ],
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }


def por_uf(session: Session) -> list[dict]:
    """Quantas obras cada estado tem em cada situação (UF principal da obra): a camada
    "Obras" do mapa e o resumo da página do estado."""
    linhas = session.execute(
        select(
            ObraFederal.uf, ObraFederal.situacao, func.count(), func.sum(ObraFederal.valor_previsto)
        )
        .where(ObraFederal.uf.is_not(None))
        .group_by(ObraFederal.uf, ObraFederal.situacao)
    ).all()
    ufs: dict[str, dict] = {}
    for uf, situacao, n, valor in linhas:
        u = ufs.setdefault(uf, {"uf": uf, "total": 0, "por_situacao": []})
        u["total"] += n
        u["por_situacao"].append(
            {"situacao": situacao or "Sem situação", "obras": n, "valor_previsto": valor or 0}
        )
    for u in ufs.values():
        u["por_situacao"].sort(key=lambda g: _ordem(g["situacao"]))
    return sorted(ufs.values(), key=lambda u: u["uf"])


def resumo_ufs(session: Session) -> dict:
    return {
        "ufs": por_uf(session),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em(session),
    }
